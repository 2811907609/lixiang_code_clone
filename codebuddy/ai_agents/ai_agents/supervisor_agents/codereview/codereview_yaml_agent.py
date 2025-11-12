import json
from typing import Union, Dict, Any
from pathlib import Path

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.micro_agents.yaml_agent_factory import YamlConfiguredAgent
from ai_agents.tools.codereview.file_ops.review_content_manager import (
    read_review_content_file,
)
from ai_agents.supervisor_agents.codereview.call_tracker import get_call_tracker


class CodeReviewProcessingError(Exception):
    """代码审查处理过程中的自定义异常，自动创建标准化错误响应"""

    def __init__(self, task_id: str, original_error: Exception):
        """
        初始化代码审查处理异常

        Args:
            task_id: 任务ID
            original_error: 原始异常对象
        """
        self.task_id = task_id
        self.original_error = original_error

        # 自动创建标准化错误响应
        self.error_response = self._create_error_response(task_id, str(original_error))

        super().__init__(self.error_response)

    def _create_error_response(self, task_id: str, message: str) -> str:
        """
        创建标准化的错误响应

        Args:
            task_id: 任务ID
            message: 错误消息

        Returns:
            JSON格式的错误响应
        """
        error_response = {"task_id": task_id, "status": "ERROR", "message": message}
        return json.dumps(error_response, ensure_ascii=False, indent=2)

    def get_error_response(self) -> str:
        """获取格式化的错误响应"""
        return self.error_response

    def get_original_error(self) -> Exception:
        """获取原始异常"""
        return self.original_error


class CodeReviewYamlAgent(YamlConfiguredAgent):
    """
    专门用于代码评审的 YAML 配置智能体

    继承自 YamlConfiguredAgent，为代码评审场景提供专门的配置和功能。
    """

    def __init__(
        self,
        config_path: Union[str, Path, dict],
        model=None,
        memory=None,
        execution_env=None,
        logger: AgentLogger = None,
        **kwargs,
    ):
        """
        初始化代码评审 YAML 配置智能体

        Args:
            config_path: YAML 配置文件路径或配置字典
            model: 可选的模型实例
            memory: 可选的内存系统实例
            execution_env: 可选的执行环境实例
            logger: 可选的日志记录器实例
        """
        super().__init__(config_path, model, memory, execution_env, logger)

        # 在初始化时就处理 guidance 模板替换
        self.process_guidance_template(**kwargs)

    def process_guidance_template(self, **kwargs):
        """
        从配置中获取 guidance 并进行模板参数替换，直接修改配置中的 guidance

        Args:
            **kwargs: 关键字参数，用于获取模板变量
        """
        if "guidance" not in self._config or not self._config["guidance"]:
            return

        guidance = self._config["guidance"]

        # 从 kwargs 中获取模板变量
        agent_tool_template_vars = kwargs.get("agent_tool_template_vars", {})

        if not agent_tool_template_vars:
            return

        try:
            # 使用 template_vars 进行字符串格式化，直接替换配置中的 guidance
            self._config["guidance"] = guidance.format(**agent_tool_template_vars)
        except Exception as e:
            self._logger.log_error(f"guidance 模板格式化失败: {e}，保持原始 guidance")

    def process_tool_query(self, query):
        return self._process_code_review_query(query)

    def run(self, task):
        """
        重写run方法，在执行后对结果进行校验和标准化

        Args:
            task: 任务输入

        Returns:
            标准化后的结果
        """
        result = super().run(task)
        # 对结果进行校验和标准化
        normalized_result = self._normalize_agent_result(result)
        return normalized_result

    def _process_code_review_query(self, query: str) -> str:
        """
        处理代码审查查询的完整流程，使用处理器链模式

        Args:
            query (str): 输入的查询字符串

        Returns:
            str: 处理后的结果
        """
        try:
            # 构建处理器链
            processors = self._build_query_processors()

            # 创建处理上下文
            context = {
                "original_query": query,
                "task_input": None,
                "enhanced_query": None,
                "task_id": "unknown",
            }
            # 依次执行处理器
            for processor in processors:
                context = processor(context)
            return context["enhanced_query"]
        except Exception as e:
            self._logger.log_error(f"代码审查任务处理失败: {e}")
            raise CodeReviewProcessingError(context.get("task_id", "unknown"), e)

    def _build_query_processors(self):
        """
        构建查询处理器链

        Returns:
            list: 处理器函数列表
        """
        return [
            self._validate_input_processor,
            self._parse_input_processor,
            self._validate_parameters_processor,
            self._inject_content_processor,
            self._mark_call_processor,
        ]

    def _validate_input_processor(self, context):
        """输入验证处理器"""
        if not context["original_query"]:
            agent_name = self._config.get("name", "unknow_tool")
            raise ValueError(
                f"{agent_name} 调用失败：缺少输入参数, 请重新阅读工具定义，传入正确参数"
            )
        return context

    def _parse_input_processor(self, context):
        """输入解析处理器"""
        context["task_input"] = self._parse_task_input(context["original_query"])
        context["task_id"] = context["task_input"].get("task_id", "unknown")
        return context

    def _validate_parameters_processor(self, context):
        """参数校验处理器"""
        self._validate_task_parameters(context["task_input"])
        return context

    def _inject_content_processor(self, context):
        """内容注入处理器"""
        context["enhanced_query"] = self._inject_review_content(context["task_input"])
        return context

    def _mark_call_processor(self, context):
        """调用标记处理器"""
        self._mark_agent_call(context["task_input"].get("task_id"))
        return context

    def _parse_task_input(self, task) -> Dict[str, Any]:
        """
        解析任务输入，支持多种格式

        Args:
            task: 原始任务输入

        Returns:
            解析后的任务字典
        """
        task_input = task

        # 处理各种输入格式
        if isinstance(task, dict) and "query" in task:
            # 格式: {'query': 'JSON字符串'}
            query_str = task["query"]
            try:
                # 尝试将 query 字符串解析为 JSON
                task_input = json.loads(query_str)
            except json.JSONDecodeError as json_error:
                # 如果不是 JSON，尝试解析 key: value 格式
                parsed_params = {}
                for line in query_str.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, value = line.split(":", 1)
                        parsed_params[key.strip()] = value.strip()
                if parsed_params:
                    task_input = parsed_params
                else:
                    raise ValueError(
                        f"无法解析 query 参数格式。尝试解析为JSON失败: {str(json_error)}。"
                        f"也无法解析为key:value格式。请确保输入格式为有效的JSON字符串或key:value格式。"
                        f"当前query内容: {repr(query_str)}"
                    )

        # 处理字符串输入
        elif isinstance(task, str):
            try:
                # 先尝试解析为 JSON
                parsed_input = json.loads(task)
                # 如果解析出来的 JSON 包含 query 字段，进一步提取
                if isinstance(parsed_input, dict) and "query" in parsed_input:
                    query_str = parsed_input["query"]
                    try:
                        task_input = json.loads(query_str)
                    except json.JSONDecodeError:
                        # query 不是 JSON，使用原始解析结果
                        task_input = parsed_input
                else:
                    task_input = parsed_input
            except json.JSONDecodeError as json_error:
                raise ValueError(
                    f"无法解析输入参数格式。JSON解析失败: {str(json_error)}。"
                    f"请确保输入为有效的JSON格式。"
                    f"当前输入内容: {repr(task[:200])}{'...' if len(str(task)) > 200 else ''}"
                )

        return task_input

    def _validate_task_parameters(self, task_input: Dict[str, Any]) -> None:
        """
        校验任务参数

        Args:
            task_input: 解析后的任务参数
        """
        # 定义必填字段
        required_fields = ["task_id", "review_type", "working_directory"]

        # 检查必填字段
        missing_fields = []
        for field in required_fields:
            if field not in task_input or not task_input[field]:
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"缺少必填参数: {missing_fields}")

        # 特定字段格式校验
        validation_errors = []

        # 校验 task_id 格式
        task_id_value = task_input["task_id"]
        if not isinstance(task_id_value, str) or len(task_id_value) < 10:
            validation_errors.append("task_id 格式无效（应为有效的任务标识字符串）")

        # 校验 review_type
        review_type = task_input["review_type"]
        valid_types = ["file", "diff", "snippet"]
        if review_type not in valid_types:
            validation_errors.append(f"review_type 必须是以下之一: {valid_types}")

        # 校验 working_directory
        working_dir = task_input["working_directory"]
        if not isinstance(working_dir, str) or not working_dir.startswith("/"):
            validation_errors.append("working_directory 必须是绝对路径")

        if validation_errors:
            raise ValueError(f"参数校验失败: {'; '.join(validation_errors)}")

    def _inject_review_content(self, task_input: Dict[str, Any]) -> str:
        """
        注入审查内容到任务参数中

        Args:
            task_input: 校验后的任务参数

        Returns:
            包含审查内容的完整任务字符串
        """
        task_id = task_input["task_id"]

        try:
            # 读取审查内容文件
            review_content = read_review_content_file(task_id)

            # 将审查内容合并到任务参数中
            task_input["review_content"] = review_content

            # 返回JSON字符串格式
            return json.dumps(task_input, ensure_ascii=False)

        except FileNotFoundError:
            raise ValueError("审查内容文件不存在，Supervisor需要重新保存审查内容文件")
        except Exception as e:
            raise ValueError(f"读取审查内容文件失败: {str(e)}")

    def _mark_agent_call(self, task_id: str) -> None:
        """
        标记真实Agent调用

        Args:
            task_id: 任务ID
        """
        if not task_id:
            return

        call_tracker = get_call_tracker()
        agent_name = self._config.get("name", "")

        # 根据agent名称判断调用类型
        if "review" in agent_name.lower() and "verify" not in agent_name.lower():
            call_tracker.mark_agent_called(task_id, "review")
        elif "verify" in agent_name.lower():
            call_tracker.mark_agent_called(task_id, "verify")

    def _normalize_agent_result(self, result):
        """
        标准化agent工具返回结果
        将dict类型结果转换为JSON字符串，str类型直接返回

        用于解决code_act模式下，子Agent返回dict类型结果导致的json.loads解析异常问题

        Args:
            result: agent执行的原始返回结果

        Returns:
            标准化后的结果（字符串格式）
        """
        if result is None:
            return result

        # 如果已经是字符串，直接返回
        if isinstance(result, str):
            return result

        # 非字符串类型统一使用JSON序列化
        try:
            normalized_result = json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str,  # 对不可序列化的对象使用str()转换
                sort_keys=True,  # 排序键名，确保输出稳定
            )
            return normalized_result

        except (TypeError, ValueError, RecursionError):
            # 转换失败时使用str()作为兜底
            fallback_result = str(result)
            return fallback_result

    def _create_error_response(self, task_id: str, message: str) -> str:
        """
        创建标准化的错误响应

        Args:
            task_id: 任务ID
            message: 错误消息

        Returns:
            JSON格式的错误响应
        """
        error_response = {"task_id": task_id, "status": "ERROR", "message": message}
        return json.dumps(error_response, ensure_ascii=False, indent=2)
