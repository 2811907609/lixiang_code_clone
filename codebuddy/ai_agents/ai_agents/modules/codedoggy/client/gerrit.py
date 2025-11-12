from ai_agents.modules.codedoggy.server.env import get_current_env
import requests
from urllib.parse import urljoin
import logging


class GerritClient:

    def __init__(self):
        env = get_current_env()
        self.base_url = "https://gerrit.it.chehejia.com"
        self.auth = (env["config"]["gerritUserName"], env["config"]["gerritPassWord"])
        self.session = None
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def __enter__(self):
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update(self.headers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_session()

    def start_session(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.auth = self.auth
            self.session.headers.update(self.headers)

    def close_session(self):
        if self.session:
            self.session.close()
            self.session = None

    def _request(self, method, endpoint, **kwargs):
        if not self.session:
            self.start_session()
        url = urljoin(f"{self.base_url}/a/", endpoint.lstrip("/"))
        response = self.session.request(method, url, **kwargs)
        response_text = response.text

        if response_text.startswith(")]}'"):
            response_text = response_text[4:]

        try:
            if response_text:
                return response.json()
            return None
        except ValueError:
            return response_text

    def create_draft(self, change_num, revision_id, comment_input):
        request_path = f"/changes/{change_num}/revisions/{revision_id}/drafts"
        data = comment_input

        try:
            result = self._request("PUT", request_path, json=data)
            logging.info("create draft result: %s", result)
            return result
        except Exception as e:
            raise Exception("Failed to create draft: change: %s, revision: %s",
                            change_num) from e

    def set_review(self, change_num, revision_id, review_data):
        request_path = f"/changes/{change_num}/revisions/{revision_id}/review"

        try:
            result = self._request("POST", request_path, json=review_data)
            logging.info("set review result: %s", result)
            return result
        except Exception as e:
            raise Exception("Failed to set review: change: %s, revision: %s",
                            change_num, revision_id) from e
