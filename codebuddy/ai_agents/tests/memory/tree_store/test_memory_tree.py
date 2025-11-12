import pytest
import tempfile
import shutil
import json
from pathlib import Path
from ai_agents.memory.tree_store.memory_tree import HierarchicalMemorySystem, MemoryType, MemoryTypeManager


class TestMemoryTypeManager:
    """测试Memory类型管理器"""

    def test_get_display_name(self):
        """测试获取显示名称"""
        assert MemoryTypeManager.get_display_name(MemoryType.PROJECT) == "项目 Memory"
        assert MemoryTypeManager.get_display_name(MemoryType.TASK) == "任务 Memory"
        assert MemoryTypeManager.get_display_name(MemoryType.HISTORY) == "历史 Memory"

    def test_auto_detect_type(self):
        """测试自动检测Memory类型"""
        assert MemoryTypeManager.auto_detect_type("project.summary") == MemoryType.PROJECT
        assert MemoryTypeManager.auto_detect_type("codebase.structure") == MemoryType.PROJECT
        assert MemoryTypeManager.auto_detect_type("knowledge.patterns") == MemoryType.PROJECT

        assert MemoryTypeManager.auto_detect_type("task.summary") == MemoryType.TASK
        assert MemoryTypeManager.auto_detect_type("plan.overview") == MemoryType.TASK
        assert MemoryTypeManager.auto_detect_type("context.current") == MemoryType.TASK
        assert MemoryTypeManager.auto_detect_type("progress.status") == MemoryType.TASK

        assert MemoryTypeManager.auto_detect_type("history.recent_tasks") == MemoryType.HISTORY

        assert MemoryTypeManager.auto_detect_type("unknown.key") is None


class TestHierarchicalMemorySystem:
    """测试层次化内存系统"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def memory_system(self, temp_dir):
        """创建内存系统实例"""
        return HierarchicalMemorySystem(storage_dir=temp_dir)

    def test_initialization(self, memory_system, temp_dir):
        """测试初始化"""
        assert memory_system.storage_dir == Path(temp_dir)
        assert memory_system.project_dir.exists()
        assert memory_system.tasks_dir.exists()
        assert memory_system.history_dir.exists()
        assert memory_system.current_task_id is None
        assert len(memory_system.project_memory) == 0
        assert len(memory_system.task_memory) == 0
        assert len(memory_system.history_memory) == 0

    def test_project_content_operations(self, memory_system):
        """测试项目内容操作"""
        # 更新项目内容
        memory_system.update_project_content(
            "project.summary",
            "这是一个测试项目",
            "初始化项目描述"
        )

        # 验证内容
        assert "project.summary" in memory_system.project_memory
        assert "这是一个测试项目" in memory_system.project_memory["project.summary"]
        assert "初始化项目描述" in memory_system.project_memory["project.summary"]

        # 追加内容
        memory_system.update_project_content(
            "project.summary",
            "追加的内容",
            "添加更多信息",
            mode="append"
        )

        assert "追加的内容" in memory_system.project_memory["project.summary"]

    def test_task_operations(self, memory_system):
        """测试任务操作"""
        # 创建新任务
        memory_system.new_task("task_001", description="测试任务")

        assert memory_system.current_task_id == "task_001"
        assert "task.summary" in memory_system.task_memory
        assert "测试任务" in memory_system.task_memory["task.summary"]

        # 更新任务内容
        memory_system.update_task_content("task.progress.status", "进行中")
        assert memory_system.task_memory["task.progress.status"] == "进行中"

        # 设置当前任务
        memory_system.set_current_task("task_001")
        assert memory_system.current_task_id == "task_001"

    def test_parent_child_tasks(self, memory_system):
        """测试父子任务"""
        # 创建父任务
        memory_system.new_task("task_001", description="父任务")
        memory_system.update_task_content("task.context.shared", "共享上下文")

        # 创建子任务
        memory_system.new_task("task_001.1", "task_001", "子任务")

        # 验证子任务继承了父任务的内容
        assert memory_system.current_task_id == "task_001.1"
        assert "task.context.shared" in memory_system.task_memory
        assert memory_system.task_memory["task.context.shared"] == "共享上下文"

    def test_task_completion(self, memory_system):
        """测试任务完成"""
        # 创建并完成任务
        memory_system.new_task("task_001", description="测试任务")
        memory_system.update_task_content("task.results", "任务结果")

        result = memory_system.complete_task("任务已完成")

        assert memory_system.current_task_id is None
        assert "Task completed and recorded in history" in result
        assert "history.recent_tasks" in memory_system.history_memory

    def test_get_content(self, memory_system):
        """测试获取内容"""
        # 准备测试数据
        memory_system.update_project_content("project.summary", "项目摘要", "测试")
        memory_system.new_task("task_001", description="测试任务")

        # 测试自动检测类型
        content = memory_system.get_content(["project.summary"], "auto")
        assert "项目摘要" in content
        assert "项目 Memory" in content

        # 测试指定类型
        content = memory_system.get_content(["task.summary"], "task")
        assert "测试任务" in content
        assert "任务 Memory" in content

        # 测试不存在的内容
        content = memory_system.get_content(["nonexistent.key"], "auto")
        assert "未找到任何指定的内容" in content

    def test_delete_content(self, memory_system):
        """测试删除内容"""
        # 添加内容
        memory_system.update_project_content("project.test", "测试内容", "测试")
        assert "project.test" in memory_system.project_memory

        # 删除内容
        memory_system.delete_content("project.test", "project")
        assert "project.test" not in memory_system.project_memory

    def test_overview_methods(self, memory_system):
        """测试概览方法"""
        # 测试项目概览
        memory_system.update_project_content("project.summary", "项目摘要", "测试")
        memory_system.update_project_content("project.architecture.summary", "架构摘要", "测试")

        overview = memory_system.get_project_overview()
        assert "项目概览" in overview
        assert "项目摘要" in overview
        assert "architecture" in overview

        # 测试任务概览
        memory_system.new_task("task_001", description="测试任务")
        overview = memory_system.get_task_overview()
        assert "任务概览" in overview
        assert "task_001" in overview
        assert "测试任务" in overview

        # 测试无任务时的概览
        memory_system.current_task_id = None
        overview = memory_system.get_task_overview()
        assert "当前没有活跃任务" in overview

    def test_incremental_save(self, memory_system, temp_dir):
        """测试增量保存"""
        # 更新项目内容
        memory_system.update_project_content("project.test1", "内容1", "测试")
        memory_system.update_project_content("project.test2", "内容2", "测试")

        # 验证文件存在
        assert (Path(temp_dir) / "project" / "project.test1.json").exists()
        assert (Path(temp_dir) / "project" / "project.test2.json").exists()
        assert (Path(temp_dir) / "project" / "keys.json").exists()

        # 删除一个key
        memory_system.delete_content("project.test1", "project")

        # 验证文件被删除
        assert not (Path(temp_dir) / "project" / "project.test1.json").exists()
        assert (Path(temp_dir) / "project" / "project.test2.json").exists()

        # 验证keys.json被更新
        with open(Path(temp_dir) / "project" / "keys.json", 'r', encoding='utf-8') as f:
            keys = json.load(f)
        assert "project.test1" not in keys
        assert "project.test2" in keys

    def test_flush_all_changes(self, memory_system):
        """测试手动保存所有变化"""
        # 添加一些内容
        memory_system.update_project_content("project.test", "测试", "测试")
        memory_system.new_task("task_001", description="测试")
        memory_system.update_task_content("task.test", "测试")

        # 手动保存所有变化
        memory_system.flush_all_changes()

        # 验证变化跟踪被清空
        assert len(memory_system.project_changes) == 0
        assert len(memory_system.task_changes) == 0
        assert len(memory_system.history_changes) == 0

    def test_persistence(self, temp_dir):
        """测试持久化"""
        # 创建第一个实例并添加数据
        memory1 = HierarchicalMemorySystem(storage_dir=temp_dir)
        memory1.update_project_content("project.test", "持久化测试", "测试")
        memory1.new_task("task_001", description="持久化任务")
        memory1.update_task_content("task.test", "任务内容")

        # 创建第二个实例，验证数据被正确加载
        memory2 = HierarchicalMemorySystem(storage_dir=temp_dir)
        assert "project.test" in memory2.project_memory
        assert "持久化测试" in memory2.project_memory["project.test"]
        assert memory2.current_task_id == "task_001"
        assert "task.test" in memory2.task_memory
        assert memory2.task_memory["task.test"] == "任务内容"


class TestMemoryTools:
    """测试Memory工具函数"""

    @pytest.fixture
    def memory_system(self):
        """创建内存系统实例"""
        temp_dir = tempfile.mkdtemp()
        system = HierarchicalMemorySystem(storage_dir=temp_dir)
        yield system
        shutil.rmtree(temp_dir)

    def test_memory_tools_creation(self, memory_system):
        """测试工具函数创建"""
        tools = memory_system.tools()
        assert len(tools) == 5  # 应该有5个工具函数

        # 验证所有工具都是可调用的
        for tool in tools:
            assert callable(tool)

    def test_core_functionality_through_methods(self, memory_system):
        """通过直接调用方法测试核心功能"""
        # 测试创建新任务
        memory_system.new_task("task_001", description="测试任务")
        assert memory_system.current_task_id == "task_001"

        # 测试获取任务概览
        overview = memory_system.get_task_overview()
        assert "任务概览" in overview
        assert "task_001" in overview

        # 测试更新任务内容
        memory_system.update_task_content("task.progress", "进行中")
        assert memory_system.task_memory["task.progress"] == "进行中"

        # 测试获取内容
        content = memory_system.get_content(["task.progress"], "task")
        assert "进行中" in content

        # 测试完成任务
        result = memory_system.complete_task("任务完成", False)
        assert "Task completed and recorded in history" in result
        assert memory_system.current_task_id is None

    def test_project_operations_through_methods(self, memory_system):
        """测试项目操作方法"""
        # 测试更新项目信息
        memory_system.update_project_content("project.test", "测试内容", "测试理由")
        assert "project.test" in memory_system.project_memory
        assert "测试内容" in memory_system.project_memory["project.test"]
        assert "测试理由" in memory_system.project_memory["project.test"]

        # 测试获取项目概览
        overview = memory_system.get_project_overview()
        assert "项目概览" in overview
        assert "project" in overview

    def test_error_handling(self, memory_system):
        """测试错误处理"""
        # 测试在没有当前任务时更新任务内容
        with pytest.raises(ValueError, match="No current task set"):
            memory_system.update_task_content("task.test", "内容")

        # 测试不支持的Memory类型
        with pytest.raises(ValueError, match="Unsupported memory type"):
            memory_system.delete_content("test.key", "invalid_type")


class TestEdgeCases:
    """测试边界情况和特殊场景"""

    @pytest.fixture
    def memory_system(self):
        """创建内存系统实例"""
        temp_dir = tempfile.mkdtemp()
        system = HierarchicalMemorySystem(storage_dir=temp_dir)
        yield system
        shutil.rmtree(temp_dir)

    def test_empty_content_operations(self, memory_system):
        """测试空内容操作"""
        # 测试获取空的keys列表
        content = memory_system.get_content([], "auto")
        assert "没有指定要获取的键值" in content

        # 测试空项目Memory的概览
        overview = memory_system.get_project_overview()
        assert "项目 Memory 为空" in overview

    def test_markdown_generation(self, memory_system):
        """测试markdown文件生成"""
        # 添加一些层次化的内容
        memory_system.update_project_content("project.summary", "项目摘要", "测试")
        memory_system.update_project_content("project.architecture.overview", "架构概览", "测试")
        memory_system.update_project_content("project.architecture.patterns", "设计模式", "测试")

        # 验证markdown文件被生成
        project_md = memory_system.storage_dir / "project" / "project.md"
        assert project_md.exists()

        # 验证markdown内容
        with open(project_md, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "PROJECT" in content
        assert "项目摘要" in content
        assert "架构概览" in content
        assert "设计模式" in content

    def test_task_template_application(self, memory_system):
        """测试任务模板应用"""
        memory_system.new_task("task_001", description="测试任务")

        # 验证模板keys被创建
        expected_keys = [
            "task.summary",
            "task.plan.overview",
            "task.context.current",
            "task.progress.status"
        ]

        for key in expected_keys:
            assert key in memory_system.task_memory
            if key != "task.summary":  # summary已经被设置为描述
                assert "待补充" in memory_system.task_memory[key]

    def test_history_management(self, memory_system):
        """测试历史管理"""
        # 创建并完成多个任务
        for i in range(3):
            memory_system.new_task(f"task_{i:03d}", description=f"测试任务{i}")
            memory_system.update_task_content("task.results", f"结果{i}")
            memory_system.complete_task(f"完成任务{i}")

        # 验证历史记录
        assert "history.recent_tasks" in memory_system.history_memory
        history_data = json.loads(memory_system.history_memory["history.recent_tasks"])
        assert len(history_data) == 3

        # 验证历史记录内容
        for i, record in enumerate(history_data):
            assert record["task_id"] == f"task_{i:03d}"
            assert f"完成任务{i}" in record["summary"]

    def test_parent_task_merging(self, memory_system):
        """测试父任务合并"""
        # 创建父任务
        memory_system.new_task("task_001", description="父任务")

        # 创建子任务并完成
        memory_system.new_task("task_001.1", "task_001", "子任务")
        memory_system.update_task_content("task.results", "子任务结果")
        memory_system.complete_task("子任务完成", merge_to_parent=True)

        # 验证父任务中包含子任务结果
        memory_system.set_current_task("task_001")
        assert "task.subtask_results" in memory_system.task_memory
        subtask_results = memory_system.task_memory["task.subtask_results"]
        assert "task_001.1" in subtask_results
        assert "子任务完成" in subtask_results

    def test_unsupported_update_mode(self, memory_system):
        """测试不支持的更新模式"""
        memory_system.new_task("task_001", description="测试")

        with pytest.raises(ValueError, match="Unsupported mode"):
            memory_system._update_content(MemoryType.TASK, "test.key", "content", "invalid_mode")

    def test_get_content_with_invalid_memory_type(self, memory_system):
        """测试使用无效Memory类型获取内容"""
        content = memory_system.get_content(["test.key"], "invalid_type")
        assert "不支持的Memory类型" in content

    def test_task_directory_handling(self, memory_system):
        """测试任务目录处理"""
        # 测试没有当前任务时的目录获取
        directory = memory_system._get_directory(MemoryType.TASK)
        assert directory is None

        # 设置任务后再测试
        memory_system.new_task("task_001", description="测试")
        directory = memory_system._get_directory(MemoryType.TASK)
        assert directory is not None
        assert "task_001" in str(directory)
