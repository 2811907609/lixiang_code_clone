import logging

logger = logging.getLogger(__name__)

try:
    from . import deepswe # noqa
    from . import fakevllm  # noqa
    from . import llama_model  # noqa
    from . import mistral_model  # noqa
    from . import opt  # noqa
    from . import phi_model  # noqa
    from . import qwen # noqa
    from . import zed  # noqa
    from . import deepseek_model # noqa
    from . import codellama_model # noqa
    from . import codeshell_model # noqa
    from . import refact_model # noqa
    from . import transformers # noqa
    from . import wizardcode_model  # noqa
    from . import ziya_model  # noqa
except Exception as e:
    logger.warning(f"Failed to import models: {e}")
