import yaml
import re
from typing import List, Dict, Union
from pathlib import Path

from ai_agents.lib.smolagents import AgentLogger
from ai_agents.lib.dynamic_import import load_function

from .base_micro_agent import BaseMicroAgent
from ai_agents.core import TaskType
from ai_agents.tools import (
    get_tool_by_name,
)
from ai_agents.tools.execution import create_execution_environment

class YamlConfiguredAgent(BaseMicroAgent):
    """
    基于 YAML 配置的动态智能体

    通过 YAML 配置文件定义智能体的名称、描述、工具列表等属性，
    实现智能体的快速配置和部署。
    """

    def __init__(self,
                 config: Union[dict],
                 model=None,
                 memory=None,
                 execution_env=None,
                 logger: AgentLogger=None,
                 **kwargs
                 ):
        """
        初始化 YAML 配置的智能体

        Args:
            config: 配置字典
            model: 可选的模型实例
            memory: 可选的内存系统实例
            execution_env: 可选的执行环境实例
        """
        self._config = config

        # 验证配置
        self._validate_config()

        # 如果没有提供执行环境，根据配置创建
        if execution_env is None and self._config.get('execution_env'):
            execution_env = create_execution_environment(
                self._config['execution_env'].get('type', 'host'),
                **self._config['execution_env'].get('config', {})
            )

        super().__init__(model=model, memory=memory, execution_env=execution_env, logger=logger)

        # Override tool_call_type from config if specified
        if 'tool_call_type' in self._config:
            self.tool_call_type = self._config['tool_call_type']


    def _validate_config(self):
        """验证配置文件的必要字段"""
        required_fields = ['name', 'description', 'tools']
        for field in required_fields:
            if field not in self._config:
                raise ValueError(f"配置文件缺少必要字段: {field}")

        # 验证工具配置
        for tool_config in self._config['tools']:
            if not isinstance(tool_config, dict):
                raise ValueError("工具配置必须是字典格式")
            if 'name' not in tool_config:
                raise ValueError("工具配置缺少 'name' 字段")

            # 验证动态加载工具的配置
            if 'module' in tool_config or 'function' in tool_config:
                if 'module' not in tool_config or 'function' not in tool_config:
                    raise ValueError(f"动态加载工具 '{tool_config['name']}' 必须同时包含 'module' 和 'function' 字段")

        # 验证 guidance 字段（如果存在）
        if 'guidance' in self._config:
            if not isinstance(self._config['guidance'], str):
                raise ValueError("guidance 字段必须是字符串类型")

        # 验证 agent_tool 配置（如果存在）
        if 'agent_tool' in self._config:
            agent_tool_config = self._config['agent_tool']
            if agent_tool_config.get('enabled', False):
                required_agent_tool_fields = ['function_name', 'description']
                for field in required_agent_tool_fields:
                    if field not in agent_tool_config:
                        raise ValueError(f"agent_tool 配置缺少必要字段: {field}")

        # 验证 tool_call_type 字段（如果存在）
        if 'tool_call_type' in self._config:
            tool_call_type = self._config['tool_call_type']
            if tool_call_type not in ['tool_call', 'code_act']:
                raise ValueError(f"tool_call_type 必须是 'tool_call' 或 'code_act'，当前值: {tool_call_type}")

    @property
    def name(self) -> str:
        return self._config['name']

    @property
    def description(self) -> str:
        return self._config['description']

    @property
    def default_task_type(self) -> str:
        task_type_str = self._config.get('task_type', 'CODE_GENERATION')
        # 验证 task_type_str 是否为 TaskType 类的有效属性
        if hasattr(TaskType, task_type_str):
            return getattr(TaskType, task_type_str)
        else:
            return TaskType.CODE_GENERATION

    def process_tool_query(self, query):
        return query

    def _get_tools(self):
        """根据配置获取工具列表"""
        tools = []

        # 根据配置添加工具
        for tool_config in self._config['tools']:
            tool_name = tool_config['name']

            # 检查是否是动态加载的工具
            if 'module' in tool_config and 'function' in tool_config:
                # 使用动态加载
                module = tool_config['module']
                function = tool_config['function']
                try:
                    loaded_function = load_function(module, function)
                    tools.append(loaded_function)
                except (ImportError, AttributeError, TypeError) as e:
                    raise ValueError(f"动态加载工具 '{tool_name}' 失败: {e}") from e
            else:
                # 使用现有的预定义工具加载机制
                tool_function = get_tool_by_name(tool_name)
                if tool_function is not None:
                    tools.append(tool_function)
                else:
                    raise ValueError(f"未找到工具 '{tool_name}'，请检查工具名称是否正确")
        return tools

    def agent_as_tool(self):
        """
        根据 YAML 配置动态生成 agent tool
        """
        agent_tool_config = self._config.get('agent_tool', {})

        if not agent_tool_config.get('enabled', False):
            return []

        # 从配置中提取工具函数信息
        function_name = agent_tool_config.get('function_name', 'agent_query')
        description = agent_tool_config.get('description', self.description)

        # 动态创建工具函数
        def dynamic_agent_tool(query: str) -> str:
            query = self.process_tool_query(query)
            # 如果配置中有 guidance，将其拼接到 query 前面
            if 'guidance' in self._config and self._config['guidance']:
                guidance = self._config['guidance']
                formatted_query = f"<guidance>\n{guidance}\n</guidance>\n\n{query}"
            else:
                formatted_query = query

            result = self.run(formatted_query)
            return result

        # 设置动态函数名和文档字符串
        dynamic_agent_tool.__name__ = function_name
        dynamic_agent_tool.__doc__ = description

        return [dynamic_agent_tool]


class YamlAgentFactory:
    """
    YAML Agent 工厂类

    提供基于 YAML 配置创建 agent tool 的功能。
    支持从 .yaml 文件和 .md 文件（包含 YAML 代码块）加载配置。
    """

    @staticmethod
    def _extract_yaml_from_markdown(content: str) -> tuple[dict, str]:
        """
        从 Markdown 内容中提取 YAML 配置和指导内容

        Args:
            content: Markdown 文件内容

        Returns:
            tuple: (yaml_config, guidance_content)
        """
        # 查找 YAML 代码块
        yaml_pattern = r'```yaml\s*\n(.*?)\n```'
        match = re.search(yaml_pattern, content, re.DOTALL)

        if not match:
            raise ValueError("No YAML code block found in markdown file")

        yaml_content = match.group(1)
        yaml_config = yaml.safe_load(yaml_content)

        # 移除 YAML 代码块，剩余内容作为指导
        guidance_content = re.sub(yaml_pattern, '', content, flags=re.DOTALL).strip()

        # 将指导内容添加到配置中
        if guidance_content:
            yaml_config['guidance'] = guidance_content

        return yaml_config, guidance_content

    @staticmethod
    def _load_config_from_file(config_path: Union[str, Path]) -> dict:
        """
        从文件加载配置，支持 .yaml 和 .md 文件

        Args:
            config_path: 配置文件路径

        Returns:
            dict: 解析后的配置字典
        """
        config_path = Path(config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if config_path.suffix.lower() == '.md':
            config, _ = YamlAgentFactory._extract_yaml_from_markdown(content)
            return config
        elif config_path.suffix.lower() in ['.yaml', '.yml']:
            return yaml.safe_load(content)
        else:
            raise ValueError(f"Unsupported file format: {config_path.suffix}")

    @staticmethod
    def create_agent_tool(config_path: Union[str, Path, dict],
                         agent_class=None,
                         model=None, memory=None, execution_env=None) -> List:
        """
        根据 YAML 配置创建 agent tool

        Args:
            config_path: YAML/Markdown 配置文件路径或配置字典
            agent_class: 可选的自定义智能体类，默认使用 YamlConfiguredAgent
            model: 可选的模型实例
            memory: 可选的内存系统实例
            execution_env: 可选的执行环境实例

        Returns:
            List: 包含 @tool 装饰的函数列表
        """
        # 使用自定义类或默认的 YamlConfiguredAgent
        AgentClass = agent_class or YamlConfiguredAgent

        # 如果传入的是字典，直接使用；否则从文件加载
        if isinstance(config_path, dict):
            config = config_path
        else:
            config = YamlAgentFactory._load_config_from_file(config_path)

        # 创建配置化的智能体
        agent = AgentClass(
            config=config,
            model=model,
            memory=memory,
            execution_env=execution_env
        )

        # 直接返回智能体的工具列表，这些工具已经有 @tool 装饰器
        return agent._get_tools()

    @staticmethod
    def create_agent_as_tool(config_path: Union[str, Path, dict],
                            agent_class=None,
                            model=None, memory=None,
                            execution_env=None,
                            logger: AgentLogger=None,
                            **kwargs
                            ) -> List:
        """
        根据 YAML 配置创建 agent as tool

        Args:
            config_path: YAML/Markdown 配置文件路径或配置字典
            agent_class: 可选的自定义智能体类，默认使用 YamlConfiguredAgent
            model: 可选的模型实例
            memory: 可选的内存系统实例
            execution_env: 可选的执行环境实例
            logger: 可选的日志记录器实例

        Returns:
            List: 包含动态生成的 agent tool 函数列表
        """
        # 使用自定义类或默认的 YamlConfiguredAgent
        AgentClass = agent_class or YamlConfiguredAgent

        # 如果传入的是字典，直接使用；否则从文件加载
        if isinstance(config_path, dict):
            config = config_path
        else:
            config = YamlAgentFactory._load_config_from_file(config_path)

        # 创建配置化的智能体
        agent = AgentClass(
            config=config,
            model=model,
            memory=memory,
            execution_env=execution_env,
            logger=logger,
            **kwargs
        )

        # 返回 agent as tool
        return agent.agent_as_tool()


    @staticmethod
    def create_agents_as_tools_from_folder(folder_path: Union[str, Path],
                                          agent_class=None,
                                          model=None, memory=None,
                                          execution_env=None,
                                          logger: AgentLogger=None,
                                          **kwargs
                                          ) -> List:
        """
        从文件夹中加载所有 YAML 和 Markdown 文件并创建 agent as tools

        Args:
            folder_path: 包含 YAML/Markdown 配置文件的文件夹路径
            agent_class: 可选的自定义智能体类，默认使用 YamlConfiguredAgent
            model: 可选的模型实例
            memory: 可选的内存系统实例
            execution_env: 可选的执行环境实例
            logger: 可选的日志记录器实例

        Returns:
            List: 包含所有动态生成的 agent tool 函数的列表
        """
        folder_path = Path(folder_path)
        all_tools = []

        if not folder_path.exists() or not folder_path.is_dir():
            return all_tools

        # 遍历文件夹中的所有 YAML 和 Markdown 文件
        for config_file in list(folder_path.glob("*.yaml")) + list(folder_path.glob("*.yml")) + list(folder_path.glob("*.md")):
            try:
                agent_tools = YamlAgentFactory.create_agent_as_tool(
                    config_file,
                    agent_class=agent_class,
                    model=model,
                    memory=memory,
                    execution_env=execution_env,
                    logger=logger,
                    **kwargs
                )
                all_tools.extend(agent_tools)
            except Exception as e:
                if logger:
                    logger.error(f"Failed to load agent from {config_file}: {e}")
                else:
                    print(f"加载配置文件 {config_file} 失败: {e}")

        return all_tools

    @staticmethod
    def load_agents_from_directory(directory: Union[str, Path], agent_class=None) -> Dict[str, List]:
        """
        从目录加载所有 YAML 和 Markdown 配置文件并创建 agent tools

        Args:
            directory: 包含 YAML/Markdown 配置文件的目录
            agent_class: 可选的自定义智能体类，默认使用 YamlConfiguredAgent

        Returns:
            Dict[str, List]: 智能体名称到工具列表的映射
        """
        directory = Path(directory)
        agents = {}

        # 遍历所有支持的配置文件格式
        for config_file in list(directory.glob("*.yaml")) + list(directory.glob("*.yml")) + list(directory.glob("*.md")):
            try:
                tools = YamlAgentFactory.create_agent_tool(config_file, agent_class=agent_class)
                # 读取配置获取智能体名称
                config = YamlAgentFactory._load_config_from_file(config_file)
                agent_name = config['name']
                agents[agent_name] = tools
            except Exception as e:
                print(f"加载配置文件 {config_file} 失败: {e}")

        return agents
