import logging
import time
from functools import wraps

logging.basicConfig(level=logging.DEBUG)

# 禁用numba.core的所有DEBUG日志
logging.getLogger('numba.core').setLevel(logging.WARNING)

getLogger = logging.getLogger

logger = getLogger(__name__)


def setup_logging(debug: bool = False):
    """
    Configure logging level based on debug parameter.

    Args:
        debug: If True, set log level to DEBUG; otherwise INFO
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(log_level)

    # Update existing handlers
    for handler in logging.getLogger().handlers:
        handler.setLevel(log_level)


def log_time(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f'Executing {func.__name__}')
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        duration = end - start
        logger.info(f'Duration: {duration}')
        return result

    return wrapper
