import requests
import logging
from typing import Optional, Dict, List, Union


class GitLabClient:

    def __init__(
        self,
        server_url: str,
        private_token: str,
        api_version: str = "v4",
        ssl_verify: bool = True,
        timeout: int = 30,
    ):
        """
        同步 GitLab 客户端

        :param server_url: GitLab 服务器地址 (如: https://gitlab.example.com)
        :param private_token: 个人访问令牌
        :param api_version: API 版本 (默认为 v4)
        :param ssl_verify: 是否验证 SSL 证书
        :param timeout: 请求超时时间 (秒)
        """
        self.server_url = server_url.rstrip("/")
        self.private_token = private_token
        self.api_version = api_version
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.headers = {
            "PRIVATE-TOKEN": self.private_token,
            "Content-Type": "application/json",
        }
        self.session = None  # requests 客户端会话

        logging.info("GitLabClient initialized with server_url: %s",
                     self.server_url)

    def __enter__(self):
        """支持上下文管理"""
        self.start_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时关闭会话"""
        self.close_session()

    def start_session(self):
        """初始化 requests 会话"""
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(self.headers)
            self.session.verify = self.ssl_verify

            # 测试连接
            try:
                self._request("GET", "/version")
            except Exception as e:
                self.close_session()
                raise Exception("GitLab 连接测试失败: %s", e) from e

    def close_session(self):
        """关闭 requests 会话"""
        if self.session:
            self.session.close()
            self.session = None

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Union[Dict, List]:
        """同步请求核心方法"""
        url = f"{self.server_url}/api/{self.api_version}{endpoint}"

        if not self.session:
            self.start_session()

        kwargs = {
            "params": params,
            "timeout": self.timeout,
        }

        if data:
            kwargs["data"] = data
        if json_data:
            kwargs["json"] = json_data

        try:
            response = self.session.request(method, url, **kwargs)

            if 200 <= response.status_code < 300:
                logging.info("API 请求成功: %s, response: %s", url, response.json())
                return response.json()

            error_msg = f"""
            API 请求失败: {response.status_code} - {response.reason}
            URL: {url}
            Method: {method}
            Response Body: {response.text}
            """
            raise Exception(error_msg)
        except requests.exceptions.Timeout as e:
            raise Exception("请求超时: %s", url) from e
        except requests.exceptions.RequestException as e:
            raise Exception("网络请求错误: %s", str(e)) from e

    def add_note_to_discussion(
        self,
        merge_request_iid: int,
        project_id: Union[int, str],
        comment: str,
        position: Dict,
    ) -> Dict:
        endpoint = (
            f"/projects/{project_id}/merge_requests/{merge_request_iid}/discussions"
        )
        data = {"body": comment, "position": position}
        return self._request("POST", endpoint, json_data=data)

    def get_mr_discussion(
        self,
        merge_request_iid: int,
        project_id: Union[int, str],
    ) -> Dict:
        endpoint = (
            f"/projects/{project_id}/merge_requests/{merge_request_iid}/discussions"
        )
        return self._request("GET", endpoint)
