import subprocess
import sys
import time
from pathlib import Path


class GOClient:

    def __init__(self, binary_path, env="./config.demo.json"):
        self.binary_path = Path(binary_path).absolute()
        self.env = env
        self.process = None

    def start(self):
        if not self.binary_path.exists():
            raise FileNotFoundError(
                f"Go binary not found at {self.binary_path}")
        print(self.binary_path)
        self.process = subprocess.Popen(
            [str(self.binary_path), "-env", self.env],
            # stdout=sys.stdout,  # 直接打印到终端
            stderr=sys.stderr,  # 直接打印错误到终端
            stdin=subprocess.PIPE,
        )
        # 等待服务启动
        time.sleep(2)

        if self.process.poll() is not None:
            _, stderr = self.process.communicate()
            error_msg = stderr.decode('utf-8')
            raise RuntimeError(f"Go服务启动失败: {error_msg}")

    def stop(self):
        print("stop go mcp")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
