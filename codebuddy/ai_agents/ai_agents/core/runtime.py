import uuid
import os
from dataclasses import dataclass
from importlib.metadata import version, PackageNotFoundError

from repoutils.git import get_origin
from sysutils.xhttp import encode_header_value

@dataclass
class Runtime:
    _app: str = None
    _session_id: str = None
    _biz_id: str = None # 业务ID
    _version: str = None
    _git_repo: str = None

    @property
    def app(self) -> str:
        return self._app

    @property
    def biz_id(self) -> str:
        return self._biz_id

    @biz_id.setter
    def biz_id(self, value: str):
        if self._biz_id is not None and value != self._biz_id:
            raise ValueError("Runtime.biz_id can only be set once")
        self._biz_id = value

    @app.setter
    def app(self, value: str):
        if self._app is not None and value != self._app:
            raise ValueError("Runtime.app can only be set once")
        self._app = value


    @property
    def session_id(self) -> str:
        if self._session_id is None:
            self._session_id = str(uuid.uuid4())
        return self._session_id

    @property
    def version(self) -> str:
        if self._version is None:
            try:
                self._version = version('ep-ai-agents')
            except PackageNotFoundError:
                # 如果包未找到，默认返回 dev
                self._version = 'dev'
        return self._version

    @property
    def git_repo(self) -> str:
        if self._git_repo is None:
            # 这里至少给空字符串是为了跟None区分一下，None表示未获取过
            # 空字符串表示获取了但是结果为空，这样就不需要一直重复获取了
            self._git_repo = get_origin() or ''
        return self._git_repo

    def get_custom_headers(self, agent_class_name: str = None) -> dict:
        """
        生成自定义请求头

        Args:
            agent_class_name: 智能体类名，用于构建X-Coding-Copilot-App header

        Returns:
            dict: 包含自定义headers的字典
        """

        headers = {
            "X-Coding-Copilot-Session-Id": self.session_id,
            "X-Coding-Copilot-App": f"SOPAgent/{self.app}/{agent_class_name}",
            "X-Coding-Copilot-App-Version": self.version,
            "X-Coding-Copilot-Cwd": os.getcwd(),
        }

        if self.biz_id:
            headers["X-Coding-Copilot-Biz-Id"] = self.biz_id

        if self.git_repo:
            headers["X-Coding-Copilot-Git-Repo"] = self.git_repo

        # 统一对所有header值进行编码处理
        return {k: encode_header_value(str(v)) for k, v in headers.items()}


runtime = Runtime()
