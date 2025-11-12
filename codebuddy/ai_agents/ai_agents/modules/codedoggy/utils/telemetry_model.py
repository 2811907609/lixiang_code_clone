from dataclasses import dataclass


@dataclass
class TelemetryBaseEvent:
    server: str
    web_url: str
    source_commit: str
    target_commit: str
    project_name: str
    mr_owner: str
    model: str
    execution_time_s: int = None


@dataclass
class TelemetryGerritBaseEvent(TelemetryBaseEvent):
    iid: int = None
    revision_id: int = None

    @classmethod
    def from_base_event(cls, base_event, **additional_args):
        # 复制基类所有属性并添加新属性
        args = {**vars(base_event), **additional_args}
        return cls(**args)

    def format(self, indent=None):
        """将事件转换为JSON格式的字符串

        Args:
            indent: 缩进级别，用于美化输出，默认为None

        Returns:
            str: JSON格式的事件数据
        """
        import json

        return json.dumps(vars(self), indent=indent)


@dataclass
class TelemetryGitlabBaseEvent(TelemetryBaseEvent):
    iid: int = None
    base_sha: str = None
    head_sha: str = None
    start_sha: str = None

    @classmethod
    def from_base_event(cls, base_event, **additional_args):
        # 复制基类所有属性并添加新属性
        args = {**vars(base_event), **additional_args}
        return cls(**args)

    def format(self, indent=None):
        """将事件转换为JSON格式的字符串

        Args:
            indent: 缩进级别，用于美化输出，默认为None

        Returns:
            str: JSON格式的事件数据
        """
        import json

        return json.dumps(vars(self), indent=indent)
