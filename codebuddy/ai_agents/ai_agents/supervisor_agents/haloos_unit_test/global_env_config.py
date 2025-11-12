import os


class HaloosConfig:
    def __init__(self):
        # 私有属性存储值
        self._TEST_REPO_PATH = None
        self._SOURCE_FILE_NAME = None
        self._SYSTEM_FUN_DECLARATION_PATH = None
        self._USE_HUMAN_INSTRUCT = None
        self._ENABLE_PERFORMANCE_TIMING = None

    @property
    def TEST_REPO_PATH(self):
        # 如果已设置私有值，返回私有值；否则从环境变量读取
        if self._TEST_REPO_PATH is not None:
            return self._TEST_REPO_PATH
        return os.getenv("TEST_REPO_PATH", "")

    @TEST_REPO_PATH.setter
    def TEST_REPO_PATH(self, value):
        self._TEST_REPO_PATH = value

    @property
    def SOURCE_FILE_NAME(self):
        if self._SOURCE_FILE_NAME is not None:
            return self._SOURCE_FILE_NAME
        return os.getenv("SOURCE_FILE_NAME", "")

    @SOURCE_FILE_NAME.setter
    def SOURCE_FILE_NAME(self, value):
        self._SOURCE_FILE_NAME = value

    @property
    def SYSTEM_FUN_DECLARATION_PATH(self):
        if self._SYSTEM_FUN_DECLARATION_PATH is not None:
            return self._SYSTEM_FUN_DECLARATION_PATH
        return os.getenv("SYSTEM_FUN_DECLARATION_PATH", "")

    @SYSTEM_FUN_DECLARATION_PATH.setter
    def SYSTEM_FUN_DECLARATION_PATH(self, value):
        self._SYSTEM_FUN_DECLARATION_PATH = value

    @property
    def USE_HUMAN_INSTRUCT(self):
        if self._USE_HUMAN_INSTRUCT is not None:
            return self._USE_HUMAN_INSTRUCT
        return os.getenv("USE_HUMAN_INSTRUCT", "false")

    @USE_HUMAN_INSTRUCT.setter
    def USE_HUMAN_INSTRUCT(self, value):
        self._USE_HUMAN_INSTRUCT = value

    @property
    def ENABLE_PERFORMANCE_TIMING(self):
        if self._ENABLE_PERFORMANCE_TIMING is not None:
            return self._ENABLE_PERFORMANCE_TIMING
        return os.getenv("ENABLE_PERFORMANCE_TIMING", "false")

    @ENABLE_PERFORMANCE_TIMING.setter
    def ENABLE_PERFORMANCE_TIMING(self, value):
        self._ENABLE_PERFORMANCE_TIMING = value


haloos_global_env_config = HaloosConfig()
