
import json
import time
from pathlib import Path
from typing import Dict, List
from enum import Enum
from dataclasses import dataclass


class MemoryType(Enum):
    """Memory类型枚举"""
    PROJECT = "project"
    TASK = "task"
    HISTORY = "history"
    AUTO = "auto"


@dataclass
class MemoryConfig:
    """Memory配置类"""
    name: str
    display_name: str
    key_prefixes: tuple


class MemoryTypeManager:
    """Memory类型管理器"""

    CONFIGS = {
        MemoryType.PROJECT: MemoryConfig(
            name="project",
            display_name="项目 Memory",
            key_prefixes=("project.", "codebase.", "knowledge.")
        ),
        MemoryType.TASK: MemoryConfig(
            name="task",
            display_name="任务 Memory",
            key_prefixes=("task.", "plan.", "context.", "progress.")
        ),
        MemoryType.HISTORY: MemoryConfig(
            name="history",
            display_name="历史 Memory",
            key_prefixes=("history.",)
        )
    }

    @classmethod
    def get_config(cls, memory_type: MemoryType) -> MemoryConfig:
        """获取Memory类型配置"""
        return cls.CONFIGS[memory_type]

    @classmethod
    def get_display_name(cls, memory_type: MemoryType) -> str:
        """获取显示名称"""
        return cls.CONFIGS[memory_type].display_name

    @classmethod
    def auto_detect_type(cls, key: str) -> MemoryType:
        """根据key自动检测Memory类型"""
        for memory_type, config in cls.CONFIGS.items():
            if key.startswith(config.key_prefixes):
                return memory_type
        return None


class HierarchicalMemorySystem:
    """层次化内存系统，支持项目级和任务级内存管理"""

    def __init__(self, storage_dir: str = ".memory_store", max_history_tasks: int = 10):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # 项目级内存（长期）
        self.project_dir = self.storage_dir / "project"
        self.project_dir.mkdir(exist_ok=True)

        # 任务级内存（短期）
        self.tasks_dir = self.storage_dir / "tasks"
        self.tasks_dir.mkdir(exist_ok=True)

        # 历史内存
        self.history_dir = self.storage_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

        self.max_history_tasks = max_history_tasks
        self.current_task_id = None

        # 内存数据
        self.project_memory: Dict[str, str] = {}
        self.task_memory: Dict[str, str] = {}
        self.history_memory: Dict[str, str] = {}

        # 变化跟踪：记录哪些key发生了变化
        self.project_changes: set = set()
        self.task_changes: set = set()
        self.history_changes: set = set()

        # 删除跟踪：记录哪些key被删除了
        self.project_deletions: set = set()
        self.task_deletions: set = set()
        self.history_deletions: set = set()

        self._load_from_disk()

    def _get_memory_dict(self, memory_type: MemoryType) -> Dict[str, str]:
        """根据Memory类型获取对应的内存字典"""
        if memory_type == MemoryType.PROJECT:
            return self.project_memory
        elif memory_type == MemoryType.TASK:
            return self.task_memory
        elif memory_type == MemoryType.HISTORY:
            return self.history_memory
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")

    def _get_changes_set(self, memory_type: MemoryType) -> set:
        """根据Memory类型获取对应的变化跟踪集合"""
        if memory_type == MemoryType.PROJECT:
            return self.project_changes
        elif memory_type == MemoryType.TASK:
            return self.task_changes
        elif memory_type == MemoryType.HISTORY:
            return self.history_changes
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")

    def _get_deletions_set(self, memory_type: MemoryType) -> set:
        """根据Memory类型获取对应的删除跟踪集合"""
        if memory_type == MemoryType.PROJECT:
            return self.project_deletions
        elif memory_type == MemoryType.TASK:
            return self.task_deletions
        elif memory_type == MemoryType.HISTORY:
            return self.history_deletions
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")

    def _get_directory(self, memory_type: MemoryType) -> Path:
        """根据Memory类型获取对应的存储目录"""
        if memory_type == MemoryType.PROJECT:
            return self.project_dir
        elif memory_type == MemoryType.TASK:
            return self.tasks_dir / self.current_task_id if self.current_task_id else None
        elif memory_type == MemoryType.HISTORY:
            return self.history_dir
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")

    def _load_from_disk(self):
        """从磁盘加载所有数据"""
        # 加载项目内存
        self._load_memory_section(self.project_dir, self.project_memory)

        # 加载历史内存
        self._load_memory_section(self.history_dir, self.history_memory)

        # 加载当前任务ID
        task_config = self.storage_dir / "current_task.json"
        if task_config.exists():
            with open(task_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.current_task_id = config.get("current_task_id")
                if self.current_task_id:
                    self._load_task_memory(self.current_task_id)

    def _load_memory_section(self, directory: Path, memory_dict: Dict[str, str]):
        """加载特定目录的内存数据"""
        keys_file = directory / "keys.json"
        if keys_file.exists():
            with open(keys_file, 'r', encoding='utf-8') as f:
                keys = json.load(f)

            for key in keys:
                key_file = directory / f"{key}.json"
                if key_file.exists():
                    with open(key_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        memory_dict[key] = data["content"]

    def _save_memory_section_incremental(self, memory_type: MemoryType):
        """增量保存特定Memory类型的数据"""
        directory = self._get_directory(memory_type)
        if not directory:
            return

        directory.mkdir(exist_ok=True)

        memory_dict = self._get_memory_dict(memory_type)
        changes_set = self._get_changes_set(memory_type)
        deletions_set = self._get_deletions_set(memory_type)

        # 如果没有变化，直接返回
        if not changes_set and not deletions_set:
            return

        # 处理删除的key
        for deleted_key in deletions_set:
            key_file = directory / f"{deleted_key}.json"
            if key_file.exists():
                key_file.unlink()

        # 处理更新/新增的key
        for changed_key in changes_set:
            if changed_key in memory_dict:
                content = memory_dict[changed_key]
                with open(directory / f"{changed_key}.json", 'w', encoding='utf-8') as f:
                    json.dump({"key": changed_key, "content": content}, f, ensure_ascii=False, indent=2)

        # 更新keys列表（只有在有变化时才更新）
        if changes_set or deletions_set:
            with open(directory / "keys.json", 'w', encoding='utf-8') as f:
                json.dump(list(memory_dict.keys()), f, ensure_ascii=False, indent=2)

        # 重新生成markdown（只有在有变化时才重新生成）
        if changes_set or deletions_set:
            self._dump_markdown(directory, memory_dict)

        # 清空变化跟踪
        changes_set.clear()
        deletions_set.clear()

    def _save_memory_section(self, directory: Path, memory_dict: Dict[str, str]):
        """保存特定目录的内存数据（兼容性方法，内部转换为增量保存）"""
        # 确定Memory类型
        if directory == self.project_dir:
            memory_type = MemoryType.PROJECT
        elif directory == self.history_dir:
            memory_type = MemoryType.HISTORY
        elif self.current_task_id and directory == self.tasks_dir / self.current_task_id:
            memory_type = MemoryType.TASK
        else:
            # 如果无法确定类型，回退到全量保存
            self._save_memory_section_full(directory, memory_dict)
            return

        # 标记所有key为已变化（用于兼容性）
        changes_set = self._get_changes_set(memory_type)
        changes_set.update(memory_dict.keys())

        # 执行增量保存
        self._save_memory_section_incremental(memory_type)

    def _save_memory_section_full(self, directory: Path, memory_dict: Dict[str, str]):
        """全量保存特定目录的内存数据（备用方法）"""
        # 保存keys列表
        with open(directory / "keys.json", 'w', encoding='utf-8') as f:
            json.dump(list(memory_dict.keys()), f, ensure_ascii=False, indent=2)

        # 保存每个key的内容
        for key, content in memory_dict.items():
            with open(directory / f"{key}.json", 'w', encoding='utf-8') as f:
                json.dump({"key": key, "content": content}, f, ensure_ascii=False, indent=2)

        # 生成markdown
        self._dump_markdown(directory, memory_dict)

    def _dump_markdown(self, directory: Path, memory_dict: Dict[str, str]):
        """生成markdown文件"""
        if not memory_dict:
            return

        # 按第一级路径分组
        groups = {}
        for key in memory_dict.keys():
            parts = key.split('.')
            root = parts[0]
            if root not in groups:
                groups[root] = []
            groups[root].append(key)

        # 为每个组生成markdown文件
        for root, keys in groups.items():
            keys.sort()
            content = f"# {root.upper()}\n\n"

            # 构建层次结构
            tree = {}
            for key in keys:
                parts = key.split('.')
                current = tree
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            # 生成内容
            content += self._generate_markdown_section(tree[root], root, 2, memory_dict)

            # 写入文件
            with open(directory / f"{root}.md", 'w', encoding='utf-8') as f:
                f.write(content)

    def _generate_markdown_section(self, tree_node: dict, current_path: str, level: int, memory_dict: Dict[str, str]) -> str:
        """递归生成markdown章节"""
        content = ""
        sorted_keys = sorted(tree_node.keys())

        for key in sorted_keys:
            full_key = f"{current_path}.{key}" if current_path else key

            header = "#" * level + f" {key}\n\n"
            content += header

            if full_key in memory_dict:
                content += memory_dict[full_key] + "\n\n"

            if tree_node[key]:
                content += self._generate_markdown_section(tree_node[key], full_key, level + 1, memory_dict)

        return content

    def _load_task_memory(self, task_id: str):
        """加载指定任务的内存"""
        task_dir = self.tasks_dir / task_id
        if task_dir.exists():
            self.task_memory.clear()
            self._load_memory_section(task_dir, self.task_memory)

    def _save_current_task(self):
        """保存当前任务配置和内存"""
        # 保存当前任务ID
        with open(self.storage_dir / "current_task.json", 'w', encoding='utf-8') as f:
            json.dump({"current_task_id": self.current_task_id}, f, ensure_ascii=False, indent=2)

        # 保存当前任务内存（使用增量保存）
        if self.current_task_id:
            self._save_memory_section_incremental(MemoryType.TASK)

    def set_current_task(self, task_id: str):
        """设置当前任务ID"""
        # 保存当前任务的变化（如果有的话）
        if self.current_task_id:
            self._save_memory_section_incremental(MemoryType.TASK)

        self.current_task_id = task_id
        self._load_task_memory(task_id)

        # 重置任务变化跟踪
        self.task_changes.clear()
        self.task_deletions.clear()

        self._save_current_task()

    def new_task(self, task_id: str, parent_task_id: str = None, description: str = ""):
        """创建新任务"""
        # 如果有父任务，继承其内存
        if parent_task_id:
            parent_dir = self.tasks_dir / parent_task_id
            if parent_dir.exists():
                parent_memory = {}
                self._load_memory_section(parent_dir, parent_memory)
                # 继承父任务内存作为起点
                self.task_memory = parent_memory.copy()
        else:
            self.task_memory.clear()

        # 设置任务描述
        if description:
            self.task_memory["task.summary"] = description

        # 应用任务模板
        self._apply_task_template()

        self.current_task_id = task_id
        self._save_current_task()

    def _apply_task_template(self):
        """应用简洁的任务模板"""
        template_keys = {
            "task.summary": "任务描述和目标",
            "task.plan.overview": "执行计划概述",
            "task.context.current": "当前工作上下文",
            "task.progress.status": "进度状态"
        }

        for key, placeholder in template_keys.items():
            if key not in self.task_memory:
                self.task_memory[key] = f"# {placeholder}\n\n待补充..."

    def complete_task(self, summary: str, merge_to_parent: bool = False):
        """完成当前任务"""
        if not self.current_task_id:
            return "No current task to complete"

        # 生成任务完成记录
        completion_record = {
            "task_id": self.current_task_id,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "key_results": self.task_memory.get("task.results", ""),
            "lessons_learned": self.task_memory.get("task.lessons", ""),
            "important_discoveries": self.task_memory.get("task.discoveries", "")
        }

        # 添加到历史记录
        self._add_to_history(completion_record)

        # 如果需要合并到父任务
        if merge_to_parent and '.' in self.current_task_id:
            parent_id = '.'.join(self.current_task_id.split('.')[:-1])
            self._merge_to_parent(parent_id, completion_record)

        self.current_task_id = None
        self._save_current_task()

        return "Task completed and recorded in history"

    def _add_to_history(self, completion_record: dict):
        """添加任务完成记录到历史"""
        # 加载现有历史
        recent_tasks = []
        if "history.recent_tasks" in self.history_memory:
            try:
                recent_tasks = json.loads(self.history_memory["history.recent_tasks"])
            except Exception:
                recent_tasks = []

        # 添加新记录
        recent_tasks.append(completion_record)

        # 保持最大数量限制
        if len(recent_tasks) > self.max_history_tasks:
            recent_tasks = recent_tasks[-self.max_history_tasks:]

        # 保存回历史内存
        self.history_memory["history.recent_tasks"] = json.dumps(recent_tasks, ensure_ascii=False, indent=2)

        # 记录变化并增量保存
        self.history_changes.add("history.recent_tasks")
        self._save_memory_section_incremental(MemoryType.HISTORY)

    def _merge_to_parent(self, parent_id: str, completion_record: dict):
        """将子任务结果合并到父任务"""
        parent_dir = self.tasks_dir / parent_id
        if parent_dir.exists():
            parent_memory = {}
            self._load_memory_section(parent_dir, parent_memory)

            # 合并策略：添加子任务结果到父任务
            subtask_results = parent_memory.get("task.subtask_results", "")
            subtask_results += f"\n\n## 子任务 {completion_record['task_id']}\n"
            subtask_results += f"**完成时间**: {completion_record['completed_at']}\n"
            subtask_results += f"**总结**: {completion_record['summary']}\n"
            if completion_record['key_results']:
                subtask_results += f"**关键结果**: {completion_record['key_results']}\n"

            parent_memory["task.subtask_results"] = subtask_results
            self._save_memory_section(parent_dir, parent_memory)

    # Memory操作方法
    def get_project_overview(self) -> str:
        """获取项目概览，返回可读性好的格式"""
        if not self.project_memory:
            return "项目 Memory 为空"

        result = "# 项目概览\n\n"

        # 首先显示项目总体摘要
        if "project.summary" in self.project_memory:
            result += "## 项目总结\n"
            result += self.project_memory["project.summary"] + "\n\n"

        # 按层级组织显示其他摘要
        summaries = {k: v for k, v in self.project_memory.items()
                    if k.endswith('.summary') and k != "project.summary"}

        if summaries:
            result += "## 各模块摘要\n"
            for key in sorted(summaries.keys()):
                module_name = key.replace('.summary', '').replace('project.', '')
                result += f"### {module_name}\n"
                result += summaries[key] + "\n\n"

        # 显示所有可用的keys
        result += "## 可用的 Memory 键值\n"
        keys_by_category = {}
        for key in sorted(self.project_memory.keys()):
            parts = key.split('.')
            if len(parts) >= 2:
                category = parts[1]  # project.architecture -> architecture
                if category not in keys_by_category:
                    keys_by_category[category] = []
                keys_by_category[category].append(key)

        for category in sorted(keys_by_category.keys()):
            result += f"### {category}\n"
            for key in keys_by_category[category]:
                result += f"- {key}\n"
            result += "\n"

        return result

    def get_task_overview(self) -> str:
        """获取当前任务概览，返回可读性好的格式"""
        if not self.current_task_id:
            return "当前没有活跃任务"

        if not self.task_memory:
            return f"任务 {self.current_task_id} 的 Memory 为空"

        result = f"# 任务概览: {self.current_task_id}\n\n"

        # 首先显示任务摘要
        if "task.summary" in self.task_memory:
            result += "## 任务描述\n"
            result += self.task_memory["task.summary"] + "\n\n"

        # 显示其他重要信息
        important_keys = ["task.plan.overview", "task.progress.status", "task.context.current"]
        for key in important_keys:
            if key in self.task_memory:
                section_name = key.split('.')[-1]
                result += f"## {section_name}\n"
                result += self.task_memory[key] + "\n\n"

        # 显示所有可用的keys
        result += "## 可用的任务 Memory 键值\n"
        keys_by_category = {}
        for key in sorted(self.task_memory.keys()):
            parts = key.split('.')
            if len(parts) >= 2:
                category = parts[1]  # task.plan -> plan
                if category not in keys_by_category:
                    keys_by_category[category] = []
                keys_by_category[category].append(key)

        for category in sorted(keys_by_category.keys()):
            result += f"### {category}\n"
            for key in keys_by_category[category]:
                result += f"- {key}\n"
            result += "\n"

        return result

    def get_content(self, keys: List[str], memory_type: str = "auto") -> str:
        """获取内容，返回可读性好的格式"""
        if not keys:
            return "没有指定要获取的键值"

        result = "# Memory 内容\n\n"
        found_content = False

        # 转换字符串类型为枚举
        try:
            mem_type = MemoryType(memory_type) if memory_type != "auto" else MemoryType.AUTO
        except ValueError:
            return f"不支持的Memory类型: {memory_type}"

        for key in keys:
            content = None
            source_type = ""

            if mem_type == MemoryType.AUTO:
                # 自动检测类型
                detected_type = MemoryTypeManager.auto_detect_type(key)
                if detected_type:
                    memory_dict = self._get_memory_dict(detected_type)
                    content = memory_dict.get(key)
                    source_type = MemoryTypeManager.get_display_name(detected_type)
                else:
                    # 尝试所有来源
                    for try_type in [MemoryType.PROJECT, MemoryType.TASK, MemoryType.HISTORY]:
                        memory_dict = self._get_memory_dict(try_type)
                        if key in memory_dict:
                            content = memory_dict[key]
                            source_type = MemoryTypeManager.get_display_name(try_type)
                            break
            else:
                # 指定类型
                memory_dict = self._get_memory_dict(mem_type)
                content = memory_dict.get(key)
                source_type = MemoryTypeManager.get_display_name(mem_type)

            # 格式化输出
            result += f"## {key}\n"
            result += f"**来源**: {source_type}\n\n"

            if content is not None:
                result += content + "\n\n"
                found_content = True
            else:
                result += "*内容不存在*\n\n"

        if not found_content:
            return "未找到任何指定的内容"

        return result

    def _update_content(self, memory_type: MemoryType, key: str, content: str, mode: str = 'replace', justification: str = None):
        """通用的内容更新方法"""
        memory_dict = self._get_memory_dict(memory_type)
        changes_set = self._get_changes_set(memory_type)

        if mode == 'replace':
            memory_dict[key] = content
        elif mode == 'append':
            if key in memory_dict:
                memory_dict[key] += "\n\n" + content
            else:
                memory_dict[key] = content
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        # 项目内容需要记录更新理由
        if memory_type == MemoryType.PROJECT and justification:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            update_note = f"\n\n<!-- Updated at {timestamp}: {justification} -->"
            memory_dict[key] += update_note

        # 记录变化
        changes_set.add(key)

        # 增量保存到磁盘
        self._save_memory_section_incremental(memory_type)

    def update_project_content(self, key: str, content: str, justification: str, mode: str = 'replace'):
        """更新项目内容（需要理由）"""
        self._update_content(MemoryType.PROJECT, key, content, mode, justification)

    def update_task_content(self, key: str, content: str, mode: str = 'replace'):
        """更新任务内容"""
        if not self.current_task_id:
            raise ValueError("No current task set")
        self._update_content(MemoryType.TASK, key, content, mode)

    def delete_content(self, key: str, memory_type: str = "task"):
        """删除内容"""
        try:
            mem_type = MemoryType(memory_type)
            memory_dict = self._get_memory_dict(mem_type)
            deletions_set = self._get_deletions_set(mem_type)

            if key in memory_dict:
                del memory_dict[key]
                # 记录删除操作
                deletions_set.add(key)

                # 增量保存到磁盘
                self._save_memory_section_incremental(mem_type)
        except ValueError as e:
            raise ValueError(f"Unsupported memory type: {memory_type}") from e

    def flush_all_changes(self):
        """手动保存所有待处理的变化"""
        self._save_memory_section_incremental(MemoryType.PROJECT)
        self._save_memory_section_incremental(MemoryType.TASK)
        self._save_memory_section_incremental(MemoryType.HISTORY)

    def tools(self, agent_type: str = "micro"):
        """
        根据智能体类型返回相应的memory工具

        Args:
            agent_type: 智能体类型 "supervisor" 或 "micro"
        """
        # 通用只读工具（所有agent都可以使用）
        def memory_get_project_context() -> str:
            """获取项目级长期context"""
            return self.get_project_overview()

        def memory_update_project_info(key: str, content: str, justification: str, mode: str = 'replace') -> str:
            """更新项目信息

            Args:
                key: 项目信息key，如 project.architecture.overview
                content: 更新内容，**必须使用Markdown格式**（避免JSON）
                justification: 更新理由说明
                mode: 'replace' 或 'append'
            """
            try:
                self.update_project_content(key, content, justification, mode)
                return f"成功更新项目信息: {key}\n更新理由: {justification}"
            except Exception as e:
                return f"更新项目信息失败: {str(e)}"

        def memory_get_task_overview() -> str:
            """获取当前任务的所有context"""
            return self.get_task_overview()

        def memory_get_content(keys: str, memory_type: str = "auto") -> str:
            """获取指定keys的内容

            Args:
                keys: 逗号分隔的key列表
                memory_type: 'auto', 'project', 'task', 'history'
            """
            key_list = [k.strip() for k in keys.split(',')]
            return self.get_content(key_list, memory_type)

        def memory_update_task_content(key: str, content: str, mode: str = 'replace') -> str:
            """更新任务内容

            Args:
                key: 任务内容key，如 task.progress.status
                content: 更新内容，**必须使用Markdown格式**（避免JSON）
                mode: 'replace' 或 'append'
            """
            try:
                self.update_task_content(key, content, mode)
                action = "替换" if mode == 'replace' else "追加"
                return f"成功{action}任务内容: {key}"
            except Exception as e:
                return f"更新任务内容失败: {str(e)}"

        def memory_get_history() -> str:
            """获取历史任务信息"""
            return self.get_content(["history.recent_tasks"], "history")

        def memory_complete_task(summary: str, merge_to_parent: bool = False) -> str:
            """完成当前任务

            Args:
                summary: 任务完成总结，**必须使用Markdown格式**
                merge_to_parent: 是否合并到父任务
            """
            try:
                result = self.complete_task(summary, merge_to_parent)
                return f"{result}"
            except Exception as e:
                return f"完成任务失败: {str(e)}"

        # 根据agent类型返回不同的工具集
        if agent_type == "supervisor":
            return [
                memory_get_project_context,
                memory_update_project_info,
                memory_get_task_overview,
                memory_get_content,
                memory_update_task_content,
                memory_get_history,
                memory_complete_task,
            ]
        else:
            return [
                memory_get_project_context,
                memory_get_task_overview,
                memory_get_content,
                memory_update_task_content,
                memory_get_history,
            ]
