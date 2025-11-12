import logging

logger = logging.getLogger(__name__)

# import sentence_transformers embedding related modules
try:
    from . import sentence_transformers  # noqa
except ImportError:
    logger.info("sentence_transformers not installed")
