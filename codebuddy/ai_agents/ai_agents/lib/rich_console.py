
from rich.console import Console

class DualConsole:
    def __init__(self, log_file_path, *args, **kwargs):
        # 创建控制台实例
        self.console = Console(*args, **kwargs)
        self._closed = False

        if log_file_path:
            self.log_file = open(log_file_path, 'w', encoding='utf-8')
            self.file_console = Console(file=self.log_file, width=self.console.width)
        else:
            self.log_file = None
            self.file_console = None

    def print(self, *args, **kwargs):
        # 输出到控制台
        self.console.print(*args, **kwargs)
        # 输出到文件
        if not self._closed and self.file_console and self.log_file:
            self.file_console.print(*args, **kwargs)
            # 强制刷新缓冲区
            self.log_file.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __getattr__(self, name):
        """将其他属性代理到主控制台"""
        return getattr(self.console, name)
