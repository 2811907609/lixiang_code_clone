#!/usr/bin/env python
# coding=utf-8

from datetime import datetime
from rich.console import Console
from rich.text import Text
from smolagents import AgentLogger, LogLevel


TIMESTAMP_STYLE = "#808080"  # 灰色时间戳


class TimeEnhancedAgentLogger(AgentLogger):
    """
    简化的时间增强日志器，只重写核心 log 方法
    """

    def __init__(self,
                 level: LogLevel = LogLevel.INFO,
                 console: Console | None = None,
                 show_timestamp: bool = True,
                 timestamp_format: str = "%Y-%m-%d %H:%M:%S"):
        """
        初始化简化的时间日志器

        Args:
            level: 日志级别
            console: Rich Console 实例
            show_timestamp: 是否显示时间戳
            timestamp_format: 时间戳格式，默认为 "YYYY-MM-DD HH:MM:SS"
        """
        super().__init__(level, console)
        self.show_timestamp = show_timestamp
        self.timestamp_format = timestamp_format

    def _get_timestamp_prefix(self) -> Text:
        """获取时间戳前缀"""
        timestamp = datetime.now().strftime(self.timestamp_format)
        return Text(f"[{timestamp}] ", style=TIMESTAMP_STYLE)

    def log(self, *args, level: int | str | LogLevel = LogLevel.INFO, **kwargs) -> None:
        """重写核心 log 方法，添加时间戳功能"""
        if isinstance(level, str):
            level = LogLevel[level.upper()]

        if level <= self.level:
            if self.show_timestamp and args:
                # 创建时间戳前缀
                timestamp_prefix = self._get_timestamp_prefix()

                # 处理第一个参数
                first_arg = args[0]
                if isinstance(first_arg, str):
                    # 如果是字符串，直接组合
                    combined_text = timestamp_prefix + Text(first_arg)
                    self.console.print(combined_text, *args[1:], **kwargs)
                elif isinstance(first_arg, Text):
                    # 如果是 Text 对象，直接组合
                    combined_text = timestamp_prefix + first_arg
                    self.console.print(combined_text, *args[1:], **kwargs)
                else:
                    # 对于复杂对象（Panel、Rule、Group 等），先打印时间戳，再打印内容
                    self.console.print(timestamp_prefix)
                    self.console.print(*args, **kwargs)
            else:
                # 不显示时间戳或没有参数时，直接调用父类方法
                super().log(*args, level=level, **kwargs)
