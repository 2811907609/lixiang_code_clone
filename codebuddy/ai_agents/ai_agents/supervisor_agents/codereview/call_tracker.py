"""
代码审查Agent调用状态跟踪器

用于跟踪Review Agent和Verify Agent的真实调用状态，
防止监督智能体模拟执行而不是真实调用子Agent。
"""

import threading
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CallTracker:
    """Agent调用状态跟踪器"""

    def __init__(self):
        self._lock = threading.RLock()  # 使用可重入锁避免嵌套锁问题
        self._call_status: Dict[str, Dict[str, bool]] = {}

    def _ensure_task_exists(self, task_id: str) -> None:
        """确保任务存在（内部方法，不加锁）"""
        if task_id not in self._call_status:
            self._call_status[task_id] = {
                'review_agent_called': False,
                'verify_agent_called': False
            }
            logger.info(f"初始化任务调用状态: task_id={task_id}")

    def init_task(self, task_id: str) -> None:
        """初始化任务的调用状态"""
        with self._lock:
            self._ensure_task_exists(task_id)

    def mark_agent_called(self, task_id: str, agent_type: str) -> None:
        """标记Agent被真实调用"""
        with self._lock:
            self._ensure_task_exists(task_id)

            if agent_type == 'review':
                self._call_status[task_id]['review_agent_called'] = True
                logger.info(f"标记Review Agent真实调用: task_id={task_id}")
            elif agent_type == 'verify':
                self._call_status[task_id]['verify_agent_called'] = True
                logger.info(f"标记Verify Agent真实调用: task_id={task_id}")

    def is_agent_called(self, task_id: str, agent_type: str) -> bool:
        """检查Agent是否被真实调用"""
        with self._lock:
            if task_id not in self._call_status:
                return False

            if agent_type == 'review':
                return self._call_status[task_id]['review_agent_called']
            elif agent_type == 'verify':
                return self._call_status[task_id]['verify_agent_called']
            return False

    def reset_agent_status(self, task_id: str, agent_type: str) -> None:
        """重置Agent调用状态（用于重试）"""
        with self._lock:
            self._ensure_task_exists(task_id)

            if agent_type == 'review':
                self._call_status[task_id]['review_agent_called'] = False
                logger.info(f"重置Review Agent调用状态: task_id={task_id}")
            elif agent_type == 'verify':
                self._call_status[task_id]['verify_agent_called'] = False
                logger.info(f"重置Verify Agent调用状态: task_id={task_id}")

    def cleanup_task(self, task_id: str) -> None:
        """清理任务的调用状态"""
        with self._lock:
            if task_id in self._call_status:
                del self._call_status[task_id]
                logger.info(f"清理任务调用状态: task_id={task_id}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, bool]]:
        """获取任务的完整调用状态"""
        with self._lock:
            return self._call_status.get(task_id, None)


# 全局调用跟踪器实例
_global_call_tracker = CallTracker()


def get_call_tracker() -> CallTracker:
    """获取全局调用跟踪器实例"""
    return _global_call_tracker
